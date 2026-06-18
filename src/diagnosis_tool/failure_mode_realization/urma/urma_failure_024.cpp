#include "urma_failure_024.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure024> g_urma("urma_024");

bool UrmaFailure024::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_init") != std::string::npos &&
           message.find("Failed to init bondp netlink context.") != std::string::npos;
}

std::string UrmaFailure024::GetName() const
{
    return "初始化URMA资源执行失败导致初始化URMA资源失败";
}

std::string UrmaFailure024::GetRootCauseDesc() const
{
    return "bondp_init执行初始化URMA资源时依赖的初始化URMA资源步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure024::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure024::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure024::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_init，Failed to init bondp netlink context.。";
}

std::string UrmaFailure024::GetId() const
{
    return "urma_024";
}
} // namespace diag
