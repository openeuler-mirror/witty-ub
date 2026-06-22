#include "urma_failure_194.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure194> g_urma("urma_194");

bool UrmaFailure194::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jfr") != std::string::npos &&
           message.find("Invalid parameter, trans_mode:") != std::string::npos;
}

std::string UrmaFailure194::GetName() const
{
    return "URMA context、JFR配置、JFC无效导致创建JFR失败";
}

std::string UrmaFailure194::GetRootCauseDesc() const
{
    return "urma_create_jfr用于创建JFR，调用方传入的URMA context、JFR配置、JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure194::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure194::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure194::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jfr，Invalid parameter, trans_mode:。";
}

std::string UrmaFailure194::GetId() const
{
    return "urma_194";
}
} // namespace diag
