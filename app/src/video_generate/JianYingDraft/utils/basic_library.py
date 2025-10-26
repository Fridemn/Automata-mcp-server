class StringHelper:
    @staticmethod
    def upper_first_char(s: str) -> str:
        """
        将字符串的首字母大写
        """
        if not s:
            return s
        return s[0].upper() + s[1:]


class DynamicImporter:
    @staticmethod
    def load_class(module_path: str, class_name: str, **kwargs):
        """
        动态导入模块并实例化类
        :param module_path: 模块路径
        :param class_name: 类名
        :param kwargs: 初始化参数
        :return: 类实例
        """
        import importlib

        module = importlib.import_module(module_path, package=__package__)
        cls = getattr(module, class_name)
        return cls(**kwargs)
