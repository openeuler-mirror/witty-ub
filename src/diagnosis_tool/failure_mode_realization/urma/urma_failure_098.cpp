#include "urma_failure_098.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure098> g_urma("urma_098");

bool UrmaFailure098::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_import_jfr_ex") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure098::GetName() const
{
    return "URMA context、token_value、rjfr、配置参数无效导致导入JFR失败";
}

std::string UrmaFailure098::GetRootCauseDesc() const
{
    return "urma_import_jfr_ex用于导入JFR，调用方传入的URMA "
           "context、token_value、rjfr、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure098::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure098::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure098::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_import_jfr_ex，Invalid parameter.。";
}

std::string UrmaFailure098::GetId() const
{
    return "urma_098";
}
} // namespace diag
