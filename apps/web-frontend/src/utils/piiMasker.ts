/**
 * PII 부분 마스킹 유틸리티
 *
 * 백엔드에서 복원된 개인정보를 프론트엔드에서 부분 마스킹하여 표시합니다.
 *
 * 마스킹 규칙:
 * - 이름: 중간/끝 글자 마스킹 (김철수 → 김*수)
 * - 전화번호: 중간 번호 마스킹 (010-1234-5678 → 010-****-5678)
 * - 이메일: 앞부분 일부 마스킹 (kim.cs@example.com → ki****@example.com)
 * - 주민번호: 뒷자리 전체 마스킹 (760815-1234567 → 760815-*******)
 * - 계좌번호: 중간 번호 마스킹 (123-45-678901 → 123-**-****01)
 * - 주소: 시/도만 유지 (서울특별시 강남구 테헤란로 123 → 서울특별시 ***)
 */

/**
 * 한국어 이름 부분 마스킹
 * - 2글자: 이준 → 이*
 * - 3글자: 김철수 → 김*수
 * - 4글자: 김철수아 → 김**아
 */
export function maskKoreanName(name: string): string {
  if (!name) return name;

  // 한글 이름 패턴 (2-4글자)
  const koreanNameRegex = /^[가-힣]{2,4}$/;
  if (!koreanNameRegex.test(name)) return name;

  const len = name.length;
  if (len === 2) {
    return name[0] + '*';
  } else if (len === 3) {
    return name[0] + '*' + name[2];
  } else if (len === 4) {
    return name[0] + '**' + name[3];
  }
  return name;
}

/**
 * 전화번호 부분 마스킹
 * 010-1234-5678 → 010-****-5678
 * 01012345678 → 010****5678
 */
export function maskPhoneNumber(phone: string): string {
  if (!phone) return phone;

  // 하이픈 있는 형식
  const hyphenPattern = /(\d{2,3})-(\d{3,4})-(\d{4})/;
  const hyphenMatch = phone.match(hyphenPattern);
  if (hyphenMatch) {
    return `${hyphenMatch[1]}-****-${hyphenMatch[3]}`;
  }

  // 하이픈 없는 형식
  const noHyphenPattern = /(\d{3})(\d{4})(\d{4})/;
  const noHyphenMatch = phone.match(noHyphenPattern);
  if (noHyphenMatch) {
    return `${noHyphenMatch[1]}****${noHyphenMatch[3]}`;
  }

  return phone;
}

/**
 * 이메일 부분 마스킹
 * kim.cs@example.com → ki****@example.com
 */
export function maskEmail(email: string): string {
  if (!email || !email.includes('@')) return email;

  const [localPart, domain] = email.split('@');
  if (localPart.length <= 2) {
    return `${localPart[0]}****@${domain}`;
  }

  const visible = localPart.substring(0, 2);
  return `${visible}****@${domain}`;
}

/**
 * 주민번호 부분 마스킹
 * 760815-1234567 → 760815-*******
 */
export function maskRRN(rrn: string): string {
  if (!rrn) return rrn;

  // 하이픈 있는 형식
  const hyphenPattern = /(\d{6})-(\d{7})/;
  const hyphenMatch = rrn.match(hyphenPattern);
  if (hyphenMatch) {
    return `${hyphenMatch[1]}-*******`;
  }

  // 하이픈 없는 13자리
  const noHyphenPattern = /^(\d{6})(\d{7})$/;
  const noHyphenMatch = rrn.match(noHyphenPattern);
  if (noHyphenMatch) {
    return `${noHyphenMatch[1]}*******`;
  }

  return rrn;
}

/**
 * 계좌번호 부분 마스킹
 * 123-45-678901 → 123-**-****01
 */
export function maskAccountNumber(account: string): string {
  if (!account) return account;

  // 하이픈 있는 형식
  const hyphenPattern = /(\d{3,4})-(\d{2,6})-(\d{6,10})/;
  const hyphenMatch = account.match(hyphenPattern);
  if (hyphenMatch) {
    const lastTwo = hyphenMatch[3].slice(-2);
    return `${hyphenMatch[1]}-**-****${lastTwo}`;
  }

  return account;
}

/**
 * 주소 부분 마스킹
 * 서울특별시 강남구 테헤란로 123 → 서울특별시 ***
 * 경기도 성남시 분당구 판교역로 100 → 경기도 성남시 ***
 */
export function maskAddress(address: string): string {
  if (!address) return address;

  // 광역시/특별시/도 패턴
  const metroPattern = /^(서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|세종특별자치시|제주특별자치도)\s*/;
  const metroMatch = address.match(metroPattern);
  if (metroMatch) {
    return `${metroMatch[1]} ***`;
  }

  // 도 + 시 패턴
  const doPattern = /^(경기도|강원도|충청북도|충청남도|전라북도|전라남도|경상북도|경상남도)\s+([가-힣]+시)/;
  const doMatch = address.match(doPattern);
  if (doMatch) {
    return `${doMatch[1]} ${doMatch[2]} ***`;
  }

  // 시작 부분만 유지
  const words = address.split(' ');
  if (words.length > 1) {
    return `${words[0]} ***`;
  }

  return address;
}

/**
 * 텍스트 내의 모든 PII를 부분 마스킹
 * 백엔드에서 복원된 응답 텍스트에 적용
 */
export function applyPartialMasking(text: string): string {
  if (!text) return text;

  let result = text;

  // 1. 주민번호 마스킹 (가장 먼저 - 다른 패턴과 겹칠 수 있음)
  result = result.replace(
    /\d{6}-\d{7}/g,
    (match) => maskRRN(match)
  );
  result = result.replace(
    /(?<!\d)\d{13}(?!\d)/g,
    (match) => maskRRN(match)
  );

  // 2. 전화번호 마스킹
  result = result.replace(
    /01[016789]-\d{3,4}-\d{4}/g,
    (match) => maskPhoneNumber(match)
  );
  result = result.replace(
    /0\d{1,2}-\d{3,4}-\d{4}/g,
    (match) => maskPhoneNumber(match)
  );

  // 3. 이메일 마스킹
  result = result.replace(
    /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
    (match) => maskEmail(match)
  );

  // 4. 계좌번호 마스킹
  result = result.replace(
    /\d{3,4}-\d{2,6}-\d{6,10}/g,
    (match) => maskAccountNumber(match)
  );

  // 5. 한국 주소 마스킹 (시/도로 시작하는 긴 주소)
  const addressPatterns = [
    /(서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|세종특별자치시|제주특별자치도)\s+[가-힣]+구?\s+[가-힣0-9\s,.-]+/g,
    /(경기도|강원도|충청북도|충청남도|전라북도|전라남도|경상북도|경상남도)\s+[가-힣]+시\s+[가-힣0-9\s,.-]+/g,
  ];

  for (const pattern of addressPatterns) {
    result = result.replace(pattern, (match) => maskAddress(match));
  }

  // 6. 한국어 이름 마스킹 (컨텍스트 기반 - "OOO님", "OOO씨", "임대인 OOO" 등)
  const nameContextPatterns = [
    /([가-힣]{2,4})님/g,
    /([가-힣]{2,4})씨/g,
    /임대인\s+([가-힣]{2,4})/g,
    /임차인\s+([가-힣]{2,4})/g,
    /피고인\s+([가-힣]{2,4})/g,
    /피해자\s+([가-힣]{2,4})/g,
    /원고\s+([가-힣]{2,4})/g,
    /피고\s+([가-힣]{2,4})/g,
    /대표이사\s+([가-힣]{2,4})/g,
    /대표자\s+([가-힣]{2,4})/g,
  ];

  for (const pattern of nameContextPatterns) {
    result = result.replace(pattern, (match, name) => {
      return match.replace(name, maskKoreanName(name));
    });
  }

  return result;
}

/**
 * 마스킹 적용 여부를 설정과 함께 결정
 */
export interface MaskingOptions {
  maskNames?: boolean;
  maskPhones?: boolean;
  maskEmails?: boolean;
  maskRRN?: boolean;
  maskAccounts?: boolean;
  maskAddresses?: boolean;
}

/**
 * 선택적 부분 마스킹 적용
 */
export function applySelectiveMasking(
  text: string,
  options: MaskingOptions = {}
): string {
  const defaultOptions: MaskingOptions = {
    maskNames: true,
    maskPhones: true,
    maskEmails: true,
    maskRRN: true,
    maskAccounts: true,
    maskAddresses: true,
  };

  const opts = { ...defaultOptions, ...options };

  if (!text) return text;

  let result = text;

  // 주민번호
  if (opts.maskRRN) {
    result = result.replace(/\d{6}-\d{7}/g, (match) => maskRRN(match));
  }

  // 전화번호
  if (opts.maskPhones) {
    result = result.replace(
      /01[016789]-\d{3,4}-\d{4}/g,
      (match) => maskPhoneNumber(match)
    );
  }

  // 이메일
  if (opts.maskEmails) {
    result = result.replace(
      /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
      (match) => maskEmail(match)
    );
  }

  // 계좌번호
  if (opts.maskAccounts) {
    result = result.replace(
      /\d{3,4}-\d{2,6}-\d{6,10}/g,
      (match) => maskAccountNumber(match)
    );
  }

  // 주소
  if (opts.maskAddresses) {
    const addressPatterns = [
      /(서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시)\s+[가-힣]+구?\s+[가-힣0-9\s,.-]+/g,
      /(경기도|강원도|충청북도|충청남도|전라북도|전라남도|경상북도|경상남도)\s+[가-힣]+시\s+[가-힣0-9\s,.-]+/g,
    ];

    for (const pattern of addressPatterns) {
      result = result.replace(pattern, (match) => maskAddress(match));
    }
  }

  // 이름
  if (opts.maskNames) {
    const nameContextPatterns = [
      /([가-힣]{2,4})님/g,
      /([가-힣]{2,4})씨/g,
      /임대인\s+([가-힣]{2,4})/g,
      /임차인\s+([가-힣]{2,4})/g,
    ];

    for (const pattern of nameContextPatterns) {
      result = result.replace(pattern, (match, name) => {
        return match.replace(name, maskKoreanName(name));
      });
    }
  }

  return result;
}

export default {
  maskKoreanName,
  maskPhoneNumber,
  maskEmail,
  maskRRN,
  maskAccountNumber,
  maskAddress,
  applyPartialMasking,
  applySelectiveMasking,
};
