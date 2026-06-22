#include "urma_failure_159.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure159> g_urma("urma_159");

bool UrmaFailure159::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_pcontext") != std::string::npos &&
           message.find("failed to add fd:") != std::string::npos && message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure159::GetName() const
{
    return "创建pcontext执行失败导致创建pcontext失败";
}

std::string UrmaFailure159::GetRootCauseDesc() const
{
    return "bondp_create_pcontext执行创建pcontext时依赖的创建pcontext步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure159::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure159::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure159::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_pcontext，failed to add fd:，, errno:。";
}

std::string UrmaFailure159::GetId() const
{
    return "urma_159";
}
} // namespace diag
