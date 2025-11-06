import React from 'react';

type Props = {
  asOf: string | null | undefined;
  loading?: boolean;
};

function pluralize(value: number, singular: string, plural: string) {
  return value === 1 ? `1 ${singular}` : `${value} ${plural}`;
}

function formatRelative(asOf: string | null | undefined): string {
  if (!asOf) return 'Sem atualização';
  const parsed = new Date(asOf);
  if (Number.isNaN(parsed.getTime())) {
    return 'Atualização desconhecida';
  }

  const diffMs = Date.now() - parsed.getTime();
  if (diffMs < 0) return 'Em tempo real';

  const diffMinutes = Math.floor(diffMs / 60000);
  if (diffMinutes < 1) return 'Agora';
  if (diffMinutes < 60) return pluralize(diffMinutes, 'minuto', 'minutos');

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    const remainder = diffMinutes - diffHours * 60;
    if (remainder === 0) {
      return pluralize(diffHours, 'hora', 'horas');
    }
    return `${pluralize(diffHours, 'hora', 'horas')} ${remainder} min`;
  }

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) {
    return pluralize(diffDays, 'dia', 'dias');
  }

  const diffWeeks = Math.floor(diffDays / 7);
  if (diffWeeks < 5) {
    return pluralize(diffWeeks, 'semana', 'semanas');
  }

  const diffMonths = Math.floor(diffDays / 30);
  if (diffMonths < 12) {
    return pluralize(diffMonths, 'mês', 'meses');
  }

  const diffYears = Math.floor(diffDays / 365);
  return pluralize(diffYears, 'ano', 'anos');
}

export default function UpdateBadge({ asOf, loading }: Props) {
  return (
    <span className="update-badge">
      {loading ? 'Atualizando...' : `Atualizado há ${formatRelative(asOf)}`}
    </span>
  );
}
