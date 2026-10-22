-- Agente de repertório: planos, perfis, perguntas (o que a pessoa vê) e auditoria (só o servidor vê).
--
-- Regras que o banco garante:
-- * Cada pessoa só lê o próprio perfil e as próprias perguntas (RLS).
-- * O cliente não grava pergunta nem muda o plano: quem grava é a função `perguntar`, com a chave de serviço.
-- * A vaga da cota é reservada numa transação só, com o perfil travado (reservar_pergunta): pedidos em paralelo não
--   passam do limite.
-- * A leitura da IA, as violações do filtro e o uso de tokens ficam em `auditoria`, que nenhum cliente lê (regra M10).
-- * Se a conta for apagada, o registro fica, sem dono (on delete set null): a regra M10 pede que ele seja guardado.
-- * O agente tenta tirar da pergunta o valor em reais e o voto antes de gravar (agente/registro.py; N5, N9 e LGPD).
--
-- Privilégios: desde 30/05/2026 o Supabase não dá mais acesso automático a tabela nova, nem ao service_role. Por isso
-- cada tabela tem revoke e grant explícitos.

-- ---------- planos ----------
create table public.planos (
  nome text primary key,
  perguntas_por_semana int not null check (perguntas_por_semana >= 0)
);
insert into public.planos (nome, perguntas_por_semana) values ('gratis', 3), ('pago', 100);

alter table public.planos enable row level security;
create policy "planos: qualquer pessoa logada lê" on public.planos
  for select to authenticated using (true);

-- ---------- perfis ----------
create table public.perfis (
  id uuid primary key references auth.users (id) on delete cascade,
  plano text not null default 'gratis' references public.planos (nome),
  criado_em timestamptz not null default now(),
  aceitou_termos_em timestamptz
);

alter table public.perfis enable row level security;
create policy "perfis: ver o próprio" on public.perfis
  for select to authenticated using ((select auth.uid()) = id);
-- Sem política de insert, update ou delete: o perfil nasce pelo gatilho e o plano só muda pelo servidor.

create function public.criar_perfil()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.perfis (id) values (new.id) on conflict (id) do nothing;
  return new;
end;
$$;
revoke execute on function public.criar_perfil() from public, anon, authenticated;

create trigger ao_criar_usuario
  after insert on auth.users
  for each row execute function public.criar_perfil();

-- A pessoa aceita os termos pelo site; é o único campo do perfil que ela mexe, e só para "agora".
create function public.aceitar_termos()
returns timestamptz
language sql
security definer
set search_path = ''
as $$
  update public.perfis set aceitou_termos_em = coalesce(aceitou_termos_em, now())
  where id = (select auth.uid())
  returning aceitou_termos_em;
$$;
revoke execute on function public.aceitar_termos() from public, anon;
grant execute on function public.aceitar_termos() to authenticated;

-- ---------- perguntas (o que a pessoa vê) ----------
-- A linha nasce "pendente" na reserva da vaga e vira "respondida" quando o agente responde.
create table public.perguntas (
  id bigint generated always as identity primary key,
  usuario uuid references auth.users (id) on delete set null,
  criada_em timestamptz not null default now(),
  status text not null default 'pendente' check (status in ('pendente', 'respondida')),
  pergunta text,
  resposta text,
  resposta_curta text,
  modo text
);
create index perguntas_usuario_criada_em on public.perguntas (usuario, criada_em desc);

alter table public.perguntas enable row level security;
create policy "perguntas: ver as próprias" on public.perguntas
  for select to authenticated using ((select auth.uid()) = usuario);

-- ---------- auditoria (só o servidor) ----------
create table public.auditoria (
  pergunta_id bigint primary key references public.perguntas (id) on delete cascade,
  roteador jsonb not null default '{}',
  violacoes jsonb not null default '[]',
  ia jsonb,
  uso jsonb not null default '{}'
);
alter table public.auditoria enable row level security;
-- Sem política nenhuma: só a chave de serviço lê e grava.

-- ---------- privilégios explícitos ----------
revoke all on public.planos, public.perfis, public.perguntas, public.auditoria from anon, authenticated;
grant select on public.planos, public.perfis, public.perguntas to authenticated;
grant select on public.planos to service_role;
grant select, update on public.perfis to service_role;
grant select, insert, update, delete on public.perguntas, public.auditoria to service_role;

-- ---------- cota da semana ----------
-- O que o site mostra. Janela móvel de 7 dias; conta também as pendentes. Roda com os direitos de quem chama.
create function public.minha_cota()
returns json
language sql
stable
set search_path = ''
as $$
  select json_build_object(
    'plano', p.plano,
    'limite', pl.perguntas_por_semana,
    'usadas', (select count(*)::int from public.perguntas q
               where q.usuario = p.id and q.criada_em > now() - interval '7 days'),
    'aceitou_termos', p.aceitou_termos_em is not null
  )
  from public.perfis p
  join public.planos pl on pl.nome = p.plano
  where p.id = (select auth.uid());
$$;
revoke execute on function public.minha_cota() from public, anon;
grant execute on function public.minha_cota() to authenticated;

-- A reserva da vaga, que só o servidor chama: trava o perfil, confere termos e cota e cria a linha pendente, tudo
-- na mesma transação. Dois pedidos ao mesmo tempo esperam um pelo outro no "for update".
create function public.reservar_pergunta(p_usuario uuid)
returns json
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_plano text;
  v_termos timestamptz;
  v_limite int;
  v_usadas int;
  v_id bigint;
begin
  select p.plano, p.aceitou_termos_em, pl.perguntas_por_semana
    into v_plano, v_termos, v_limite
    from public.perfis p join public.planos pl on pl.nome = p.plano
    where p.id = p_usuario
    for update of p;
  if not found then
    return json_build_object('ok', false, 'motivo', 'perfil');
  end if;
  select count(*)::int into v_usadas from public.perguntas
    where usuario = p_usuario and criada_em > now() - interval '7 days';
  if v_termos is null then
    return json_build_object('ok', false, 'motivo', 'termos',
      'cota', json_build_object('plano', v_plano, 'limite', v_limite, 'usadas', v_usadas, 'aceitou_termos', false));
  end if;
  if v_usadas >= v_limite then
    return json_build_object('ok', false, 'motivo', 'cota',
      'cota', json_build_object('plano', v_plano, 'limite', v_limite, 'usadas', v_usadas, 'aceitou_termos', true));
  end if;
  insert into public.perguntas (usuario) values (p_usuario) returning id into v_id;
  return json_build_object('ok', true, 'id', v_id,
    'cota', json_build_object('plano', v_plano, 'limite', v_limite, 'usadas', v_usadas + 1, 'aceitou_termos', true));
end;
$$;
revoke execute on function public.reservar_pergunta(uuid) from public, anon, authenticated;
grant execute on function public.reservar_pergunta(uuid) to service_role;

-- Quem se cadastrou antes desta migração também ganha perfil.
insert into public.perfis (id) select id from auth.users on conflict (id) do nothing;
