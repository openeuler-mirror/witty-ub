#include "urma_failure_095.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure095> g_urma("urma_095");

bool UrmaFailure095::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_import_jfr_compat") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure095::GetName() const
{
    return "provider未提供import_jfr_ex操作实现无效导致导入JFR、compat失败";
}

std::string UrmaFailure095::GetRootCauseDesc() const
{
    return "urma_import_jfr_compat用于导入JFR、compat，调用方传入的provider未提供import_jfr_"
           "ex操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure095::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure095::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure095::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_import_jfr_compat，Invalid parameter.。";
}

std::string UrmaFailure095::GetId() const
{
    return "urma_095";
}
} // namespace diag
