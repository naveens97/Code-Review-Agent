// Default starter code per language — each snippet is intentionally
// imperfect so it immediately demonstrates real analyzer output when
// the user hits Review without writing anything.

export const DEFAULT_CODE = {
  python: `def calculate_average(numbers=[]):
    total = 0
    for i in range(len(numbers)):
        total = total + numbers[i]
    return total / len(numbers)


scores = [82, 91, 76, 88, 95]
print("Average:", calculate_average(scores))
`,

  javascript: `function findDuplicate(arr) {
  var seen = [];
  for (var i = 0; i < arr.length; i++) {
    if (seen.indexOf(arr[i]) != -1) {
      return arr[i];
    }
    seen.push(arr[i]);
  }
  return null;
}

const numbers = [1, 3, 4, 2, 2, 5];
console.log("Duplicate:", findDuplicate(numbers));
`,

  java: `public class Main {
    static int factorial(int n) {
        int result;
        if (n == 0) return 1;
        result = n * factorial(n - 1);
        return result;
    }

    public static void main(String[] args) {
        System.out.println("5! = " + factorial(5));
        System.out.println("0! = " + factorial(0));
    }
}
`,

  c: `#include <stdio.h>

int sum_array(int arr[], int size) {
    int total = 0;
    int i;
    for (i = 0; i < size; i++) {
        total = total + arr[i];
    }
    return total;
}

int main() {
    int scores[] = {82, 91, 76, 88, 95};
    int n = sizeof(scores) / sizeof(scores[0]);
    printf("Sum: %d\\n", sum_array(scores, n));
    return 0;
}
`,

  cpp: `#include <iostream>
#include <vector>

int findMax(std::vector<int> nums) {
    int max = nums[0];
    for (int i = 1; i < nums.size(); i++) {
        if (nums[i] > max) {
            max = nums[i];
        }
    }
    return max;
}

int main() {
    std::vector<int> scores = {82, 91, 76, 88, 95};
    std::cout << "Max: " << findMax(scores) << std::endl;
    return 0;
}
`,
};

export const SUPPORTED_LANGUAGES = [
  { id: "python",     label: "Python 3",     monacoId: "python"     },
  { id: "javascript", label: "JavaScript",   monacoId: "javascript" },
  { id: "java",       label: "Java",         monacoId: "java"       },
  { id: "c",          label: "C",            monacoId: "c"          },
  { id: "cpp",        label: "C++",          monacoId: "cpp"        },
];

export const SEVERITY_META = {
  critical: { label: "Critical", color: "var(--critical)", bg: "var(--critical-bg)" },
  warning:  { label: "Warning",  color: "var(--warning)",  bg: "var(--warning-bg)"  },
  info:     { label: "Info",     color: "var(--info)",     bg: "var(--info-bg)"     },
};

export const CATEGORY_LABELS = {
  bug:             "Bug Risk",
  security:        "Security",
  style:           "Style",
  complexity:      "Complexity",
  performance:     "Performance",
  maintainability: "Maintainability",
  "best-practice": "Best Practice",
  tooling:         "Tooling",
  warning:         "Warning",
};
