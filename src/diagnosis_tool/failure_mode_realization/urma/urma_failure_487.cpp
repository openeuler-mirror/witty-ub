#include "urma_failure_487.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure487> g_urma("urma_487");

bool UrmaFailure487::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_send") != std::string::npos && message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure487::GetName() const
{
    return "URMA资源无效导致发送URMA资源失败";
}

std::string UrmaFailure487::GetRootCauseDesc() const
{
    return "urma_send用于发送URMA资源，调用方传入的URMA资源不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure487::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure487::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure487::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_send，Invalid parameter.。";
}

std::string UrmaFailure487::GetId() const
{
    return "urma_487";
}
} // namespace diag
