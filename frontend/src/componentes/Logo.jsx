// Quadrado roxo com três barrinhas, como blocos de uma agenda.
export default function Logo({ tamanho = 30 }) {
  return (
    <svg className="logo" width={tamanho} height={tamanho} viewBox="0 0 30 30" aria-hidden="true" focusable="false">
      <rect width="30" height="30" rx="8" fill="#5b2fd6" />
      <rect x="7" y="8" width="11" height="3" rx="1.5" fill="#fff" />
      <rect x="11" y="13.5" width="12" height="3" rx="1.5" fill="#c4b2fa" />
      <rect x="7" y="19" width="9" height="3" rx="1.5" fill="#fff" />
    </svg>
  );
}
