#include "urma_failure_099.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure099> g_urma("urma_099");

bool UrmaFailure099::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_unimport_jfr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure099::GetName() const
{
    return "target_jfr无效导致取消导入JFR失败";
}

std::string UrmaFailure099::GetRootCauseDesc() const
{
    return "urma_unimport_jfr用于取消导入JFR，调用方传入的target_jfr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure099::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure099::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure099::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unimport_jfr，Invalid parameter.。";
}

std::string UrmaFailure099::GetId() const
{
    return "urma_099";
}
} // namespace diag
