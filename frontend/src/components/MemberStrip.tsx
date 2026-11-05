import type { Member } from "../api/types";

interface MemberStripProps {
  members: Member[];
}

function initials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function MemberStrip({ members }: MemberStripProps) {
  if (members.length === 0) return null;

  return (
    <div className="member-strip">
      {members.map((member) => (
        <div className="member-strip__item" key={member.id} title={member.tagline ?? member.name}>
          {member.avatarUrl ? (
            <img src={member.avatarUrl} alt={member.name} className="member-strip__avatar" />
          ) : (
            <div className="member-strip__avatar member-strip__avatar--fallback">
              {initials(member.name)}
            </div>
          )}
          <span className="member-strip__name">{member.nickname ?? member.name}</span>
        </div>
      ))}
    </div>
  );
}
