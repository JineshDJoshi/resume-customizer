export interface SkillGroup { category: string; items: string[] }
export interface ExperienceItem { title: string; company: string; location: string; dates: string; bullets: string[] }
export interface ProjectItem { name: string; bullets: string[] }
export interface Resume {
  name: string;
  contact: string[];
  summary: string;
  skills: SkillGroup[];
  experience: ExperienceItem[];
  projects: ProjectItem[];
  education: string[];
  certifications: string[];
}
export interface Analysis {
  matched_keywords: string[];
  missing_keywords: string[];
  suggestions: string[];
  changes_summary: string[];
}
export interface AtsCheck { label: string; passed: boolean; tip: string }
export interface DiffSegment { t: "equal" | "add" | "del" | "br"; text: string }
export interface CustomizeResult {
  resume: Resume;
  analysis: Analysis;
  scores: { match_before: number; match_after: number; ats: number };
  ats_checks: AtsCheck[];
  diff: DiffSegment[];
  original_text: string;
  customized_text: string;
  file: { name: string; size: number };
}
export interface Version {
  id: number;
  label: string;
  sections: string[];
  result: CustomizeResult;
  coverLetter?: string;
}
export type DownloadFormat = "pdf" | "docx" | "txt";
