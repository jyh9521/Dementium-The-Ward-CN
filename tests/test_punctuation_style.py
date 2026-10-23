import hashlib,json,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
from audit_punctuation import audit,without_terminal_stop
ROOT=pathlib.Path(__file__).resolve().parents[1]

class PunctuationStyleTests(unittest.TestCase):
    def test_single_sentence_and_controls(self):
        for before,after in [('锁住了。','锁住了'),('Use the key.','Use the key'),('地图\r\n\r\n平面图。\r\n','地图\r\n\r\n平面图\r\n'),('用\x02钥匙\x01开门。\x01','用\x02钥匙\x01开门\x01'),('这是一把.357口径左轮手枪。','这是一把.357口径左轮手枪')]:
            with self.subTest(before=before):self.assertEqual(without_terminal_stop(before),after)
    def test_internal_punctuation_or_multiple_sentences_unchanged(self):
        for value in ['打不开，门把手没了。','已有句号。\r\n\r\n下一句。','前半句，\r\n后半句。','这是一张地图。上面写着西楼。','拿到钥匙！可以开门了。','选择“继续”。','等一下…','是吗？','铜钥匙！','保存：完成。','先拿钥匙；再开门。','已保存...']:
            with self.subTest(value=value):self.assertEqual(without_terminal_stop(value),value)
    def test_real_locale_has_no_eligible_terminal_stops(self):
        locale=ROOT/'locales/zh-CN';policy=json.loads((locale/'punctuation-style.json').read_text(encoding='utf-8'))
        self.assertEqual(audit(locale,policy),[])
    def test_actual_letter_in_ui_file_is_preserved(self):
        locale=ROOT/'locales/zh-CN';policy=json.loads((locale/'punctuation-style.json').read_text(encoding='utf-8'))
        self.assertEqual(policy['resources']['loc/en/examine.046'],'letter')
        self.assertEqual(policy['resources']['loc/en/examine.515'],'interaction-feedback')
    def test_protected_target_drift_is_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            p=pathlib.Path(folder);row=dict(id='doc:0',resource='doc',target='文档。')
            (p/'rows.json').write_text(json.dumps([row]),encoding='utf8')
            policy=dict(record_files=['rows.json'],resources={'doc':'document'},eligible_categories=['prompt'],preserved_targets={'doc:0':hashlib.sha256('原文。'.encode()).hexdigest()})
            with self.assertRaisesRegex(ValueError,'Protected'):audit(p,policy)

if __name__=='__main__':unittest.main()
