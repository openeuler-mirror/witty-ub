#include "urma_failure_023.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure023> g_urma("urma_023");

bool UrmaFailure023::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_init") != std::string::npos &&
           message.find("Failed to create global context.") != std::string::npos;
}

std::string UrmaFailure023::GetName() const
{
    return "下层资源创建失败导致初始化URMA资源失败";
}

std::string UrmaFailure023::GetRootCauseDesc() const
{
    return "bondp_init在初始化URMA资源过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure023::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure023::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure023::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_init，Failed to create global context.。";
}

std::string UrmaFailure023::GetId() const
{
    return "urma_023";
}
} // namespace diag
