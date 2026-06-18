#include "urma_failure_031.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure031> g_urma("urma_031");

bool UrmaFailure031::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_context") != std::string::npos &&
           message.find("Uninitialized variables") != std::string::npos;
}

std::string UrmaFailure031::GetName() const
{
    return "context状态不满足要求导致创建context失败";
}

std::string UrmaFailure031::GetRootCauseDesc() const
{
    return "bondp_create_context执行创建context时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure031::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure031::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure031::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_context，Uninitialized variables。";
}

std::string UrmaFailure031::GetId() const
{
    return "urma_031";
}
} // namespace diag
