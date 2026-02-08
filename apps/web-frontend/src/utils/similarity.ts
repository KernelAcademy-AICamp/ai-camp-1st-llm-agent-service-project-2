/**
 * Text Similarity Utilities
 *
 * Provides functions for calculating text similarity between clauses
 * using Jaccard Similarity (word-level comparison)
 */

import { KeyClause } from '../types';

/**
 * Tokenize Korean/English text into words
 * Removes punctuation and normalizes whitespace
 */
function tokenize(text: string): Set<string> {
  // Remove punctuation and split by whitespace
  const normalized = text
    .toLowerCase()
    .replace(/[^\w\s가-힣]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const words = normalized.split(' ').filter(word => word.length > 0);
  return new Set(words);
}

/**
 * Calculate Jaccard Similarity between two texts
 * @param text1 First text
 * @param text2 Second text
 * @returns Similarity score between 0 and 1
 */
export function calculateJaccardSimilarity(text1: string, text2: string): number {
  const set1 = tokenize(text1);
  const set2 = tokenize(text2);

  if (set1.size === 0 && set2.size === 0) {
    return 1; // Both empty = identical
  }

  if (set1.size === 0 || set2.size === 0) {
    return 0; // One empty = no similarity
  }

  // Calculate intersection
  const intersection = new Set([...set1].filter(x => set2.has(x)));

  // Calculate union
  const union = new Set([...set1, ...set2]);

  return intersection.size / union.size;
}

/**
 * Calculate similarity between two clauses
 * Compares both title and content
 */
export function calculateClauseSimilarity(clause1: KeyClause, clause2: KeyClause): number {
  // Combine title and content for comparison
  const text1 = `${clause1.title} ${clause1.content}`;
  const text2 = `${clause2.title} ${clause2.content}`;

  return calculateJaccardSimilarity(text1, text2);
}

/**
 * Find the most similar existing clause for a new clause
 * @param newClause The new clause to compare
 * @param existingClauses List of existing clauses
 * @returns The most similar clause and its similarity score
 */
export function findMostSimilarClause(
  newClause: KeyClause,
  existingClauses: KeyClause[]
): { clause: KeyClause | null; similarity: number } {
  if (existingClauses.length === 0) {
    return { clause: null, similarity: 0 };
  }

  let maxSimilarity = 0;
  let mostSimilar: KeyClause | null = null;

  for (const existing of existingClauses) {
    const similarity = calculateClauseSimilarity(newClause, existing);
    if (similarity > maxSimilarity) {
      maxSimilarity = similarity;
      mostSimilar = existing;
    }
  }

  return { clause: mostSimilar, similarity: maxSimilarity };
}

/**
 * Check if a clause is likely a duplicate based on similarity threshold
 * @param similarity Similarity score
 * @param threshold Threshold for considering as duplicate (default: 0.7)
 */
export function isDuplicateClause(similarity: number, threshold: number = 0.7): boolean {
  return similarity >= threshold;
}

/**
 * Get similarity level label for UI display
 */
export function getSimilarityLevel(similarity: number): {
  level: 'high' | 'medium' | 'low' | 'none';
  label: string;
  color: string;
} {
  if (similarity >= 0.8) {
    return { level: 'high', label: '매우 유사', color: '#ef4444' }; // red
  } else if (similarity >= 0.5) {
    return { level: 'medium', label: '유사', color: '#f59e0b' }; // amber
  } else if (similarity >= 0.2) {
    return { level: 'low', label: '약간 유사', color: '#3b82f6' }; // blue
  } else {
    return { level: 'none', label: '새로운 조항', color: '#10b981' }; // green
  }
}

/**
 * Process new clauses and calculate similarity with existing clauses
 * Returns new clauses with similarity information
 */
export function analyzeClauseSimilarity(
  newClauses: KeyClause[],
  existingClauses: KeyClause[]
): Array<{
  clause: KeyClause;
  similarity: number;
  similarTo: KeyClause | null;
  similarityLevel: ReturnType<typeof getSimilarityLevel>;
  isRecommendedToAdd: boolean;
}> {
  return newClauses.map(newClause => {
    const { clause: similarTo, similarity } = findMostSimilarClause(newClause, existingClauses);
    const similarityLevel = getSimilarityLevel(similarity);

    // Recommend adding if similarity is below 0.7 (not a duplicate)
    const isRecommendedToAdd = similarity < 0.7;

    return {
      clause: newClause,
      similarity,
      similarTo,
      similarityLevel,
      isRecommendedToAdd,
    };
  });
}
