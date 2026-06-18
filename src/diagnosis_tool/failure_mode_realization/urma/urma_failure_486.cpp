#include "urma_failure_486.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure486> g_urma("urma_486");

bool UrmaFailure486::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_send") != std::string::npos &&
           message.find("null pointer exists in tjfr.") != std::string::npos;
}

std::string UrmaFailure486::GetName() const
{
    return "URMA资源状态不满足要求导致发送URMA资源失败";
}

std::string UrmaFailure486::GetRootCauseDesc() const
{
    return "urma_send执行发送URMA资源时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure486::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure486::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure486::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_send，null pointer exists in tjfr.。";
}

std::string UrmaFailure486::GetId() const
{
    return "urma_486";
}
} // namespace diag
