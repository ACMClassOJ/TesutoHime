import re

from scripts.db.env import *

class NotMatched(BaseException): pass

def pattern_codeblock(problem: Problem):
    if problem.example_input is None and problem.example_output is None:
        raise NotMatched

    global description
    description = None

    def match_code(s: Optional[str]):
        if s is None:
            return None
        if s.startswith('## '): s = s[3:]
        if s.endswith('## '): s = s[:-3]
        s = s.strip().replace('\r\n', '\n')
        if re.match('^[(（]?(无|none|no|null)[）)]?$', s, re.IGNORECASE):
            return None
        if not s.startswith('```'):
            raise NotMatched
        res = '\n'.join(s.splitlines()[1:])
        res = res.split('```')
        if len(res) != 2:
            raise NotMatched
        desc = res[1].strip()
        if desc != '':
            global description
            if description is not None:
                raise NotMatched
            description = desc
        return res[0] if res[0] != '' else None

    ex = {
        'name': None,
        'input': match_code(problem.example_input),
        'output': match_code(problem.example_output),
        'description': description,
    }
    problem.examples = [ex]

def pattern_vanilla_codeblock(problem: Problem):
    if problem.example_input is None and problem.example_output is None:
        raise NotMatched

    def match_code(s: Optional[str]):
        if s is None:
            return None
        s = s.replace('\r\n', '\n').strip('\n')
        code = ''
        for line in s.splitlines():
            if code != '': code += '\n'
            if line.startswith('    '):
                code += line[4:]
            elif line.startswith('\t'):
                code += line[1:]
            else:
                raise NotMatched
        return code

    ex = {
        'name': None,
        'input': match_code(problem.example_input),
        'output': match_code(problem.example_output),
        'description': None,
    }
    problem.examples = [ex]

def pattern_codeblock_multi(problem: Problem):
    if problem.example_input is None or problem.example_output is None:
        raise NotMatched

    global name_prefix
    name_prefix = '样例'

    def match_code(s: str):
        s = s.strip().replace('\r\n', '\n')
        res = []
        while s != '':
            spl = s.splitlines()
            first = spl[0]
            if re.match('.*(input|output|输入|输出|sample|example|示例|样例).*', first, re.IGNORECASE) is None:
                raise NotMatched
            m = re.match('^[#\-*]*\s*\[?(?:<[a-z0-9]+>)?\s*(?:input|output|输入|输出)?\s*(样例|示例|sample|example)?\s*(?:input|output|输入|输出)?\s*#?[0-9一二三四五六七八九零〇十百千万:：*]*\]?\s*(?:</[a-z0-9]+>|<!--[^>]*-->)?\s*$', first, flags=re.IGNORECASE)
            if m is None:
                raise NotMatched
            if m[1] != '' and m[1] is not None:
                global name_prefix
                name_prefix = m[1]
            s = '\n'.join(spl[1:]).strip()
            if not s.startswith('```'):
                raise NotMatched
            s = '\n'.join(s.splitlines()[1:])
            spl = s.split('\n```')
            res.append(spl[0] if spl[0] != '' else None)
            s = '\n```'.join(spl[1:]).strip()
        return res

    input = match_code(problem.example_input)
    output = match_code(problem.example_output)
    if len(input) != len(output):
        raise NotMatched

    problem.examples = [{
        'name': f'{name_prefix} {i + 1}',
        'input': input[i],
        'output': output[i],
        'description': None,
    } for i in range(len(input))]

def pattern_vanilla_codeblock_multi(problem: Problem):
    if problem.example_input is None or problem.example_output is None:
        raise NotMatched

    global name_prefix
    name_prefix = '样例'

    def match_code(s: str):
        s = s.strip('\n').replace('\r\n', '\n')
        res = []
        while s != '':
            spl = s.splitlines()
            first = spl[0]
            if re.match('.*(input|output|输入|输出|sample|example|示例|样例).*', first, re.IGNORECASE) is None:
                raise NotMatched
            m = re.match('^[#\-*]*\s*\[?(?:<[a-z0-9]+>)?\s*(?:input|output|输入|输出)?\s*(样例|示例|sample|example)?\s*(?:input|output|输入|输出)?\s*#?[0-9一二三四五六七八九零〇十百千万:：*]*\]?\s*(?:</[a-z0-9]+>|<!--[^>]*-->)?\s*$', first, flags=re.IGNORECASE)
            if m is None:
                raise NotMatched
            if m[1] != '' and m[1] is not None:
                global name_prefix
                name_prefix = m[1]
            s = '\n'.join(spl[1:]).strip('\n').split('\n')
            code = ''
            while len(s) > 0:
                if s[0].startswith('    '):
                    code += '\n'
                    code += s[0][4:]
                    s = s[1:]
                elif s[0].startswith('\t'):
                    code += '\n'
                    code += s[0][1:]
                    s = s[1:]
                else:
                    break
            code = code.strip('\n')
            s = '\n'.join(s).strip()
            res.append(code)
        return res

    input = match_code(problem.example_input)
    output = match_code(problem.example_output)
    if len(input) != len(output):
        raise NotMatched

    problem.examples = [{
        'name': f'{name_prefix} {i + 1}',
        'input': input[i],
        'output': output[i],
        'description': None,
    } for i in range(len(input))]

def pattern_raw(problem: Problem):
    if problem.example_input is None and problem.example_output is None:
        raise NotMatched

    def match_code(s: Optional[str]):
        if s is None:
            return None
        s = s.strip().replace('\r\n', '\n')
        if re.match('^([0-9A-Z\-]|\s|\n)+$|^[!-~]+$', s, re.MULTILINE):
            return re.subn('\n(\s*\n)+', '\n', s, flags=re.MULTILINE)[0]
        raise NotMatched

    ex = {
        'name': None,
        'input': match_code(problem.example_input),
        'output': match_code(problem.example_output),
        'description': description,
    }
    problem.examples = [ex]

patterns = [pattern_codeblock, pattern_vanilla_codeblock, pattern_codeblock_multi, pattern_vanilla_codeblock_multi, pattern_raw]

def infer_examples(problem: Problem):
    if (
        (problem.example_input is None or problem.example_input.strip() == '') and
        (problem.example_output is None or problem.example_output.strip() == '') and
        (problem.output is None or '样例' not in problem.output) and
        (problem.description is None or
            (
                'SAMPLE' not in problem.description and
                'Sample' not in problem.description and
                'sample' not in problem.description and
                'EXAMPLE' not in problem.description and
                'Example' not in problem.description and
                'example' not in problem.description and
                '样例' not in problem.description and
                '示例' not in problem.description
            )
        )
    ) or len(problem.examples) > 0:
        print(f'skip {problem.id} {problem.title}')
        return

    for pattern in patterns:
        try:
            pattern(problem)
            print(f'ok   {problem.id}')
            return
        except NotMatched as e:
            # import traceback
            # traceback.print_exception(e)
            pass

    print(f'FAIL {problem.id} {problem.title}')

def main():
    with Session() as db:
        problems = db.scalars(sa.select(Problem).order_by(Problem.id.asc()).where(sa.or_(Problem.id < 10000, Problem.id >= 20000)))
        for problem in problems:
            infer_examples(problem)

        db.commit()

if __name__ == '__main__':
    main()
