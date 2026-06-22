#include "urma_failure_337.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure337> g_urma("urma_337");

bool UrmaFailure337::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_check_jetty_cfg_with_jetty_grp") != std::string::npos &&
           message.find("Invalid token with share_jfr.") != std::string::npos;
}

std::string UrmaFailure337::GetName() const
{
    return "Jetty、CFG、WITH状态不满足要求导致校验Jetty、CFG、WITH失败";
}

std::string UrmaFailure337::GetRootCauseDesc() const
{
    return "urma_check_jetty_cfg_with_jetty_"
           "grp执行校验Jetty、CFG、WITH时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure337::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure337::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure337::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_jetty_cfg_with_jetty_grp，Invalid token with share_jfr.。";
}

std::string UrmaFailure337::GetId() const
{
    return "urma_337";
}
} // namespace diag
