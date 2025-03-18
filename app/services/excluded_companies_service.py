class ExcludedCompaniesService:
    def __init__(self):
        self._excluded_companies = set()

    def add_excluded_companies(self, companies):
        """
        Agregar empresas a la lista de exclusión
        
        :param companies: Lista de empresas a excluir
        """
        self._excluded_companies.update(companies)

    def clear_excluded_companies(self):
        """
        Limpiar la lista de empresas excluidas
        """
        self._excluded_companies.clear()

    def get_excluded_companies(self):
        """
        Obtener lista de empresas excluidas
        
        :return: Lista de empresas excluidas
        """
        return list(self._excluded_companies)

    def is_company_excluded(self, company):
        """
        Verificar si una empresa está excluida
        
        :param company: Nombre de la empresa
        :return: Booleano indicando si la empresa está excluida
        """
        return any(
            excluded.lower() in company.lower() 
            for excluded in self._excluded_companies
        )