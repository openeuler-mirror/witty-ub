#include "urma_failure_338.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure338> g_urma("urma_338");

bool UrmaFailure338::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_check_jetty_cfg_with_jetty_grp") != std::string::npos &&
           message.find("Invalid token with unshared jfr.") != std::string::npos;
}

std::string UrmaFailure338::GetName() const
{
    return "Jetty、CFG、WITH状态不满足要求导致校验Jetty、CFG、WITH失败";
}

std::string UrmaFailure338::GetRootCauseDesc() const
{
    return "urma_check_jetty_cfg_with_jetty_"
           "grp执行校验Jetty、CFG、WITH时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure338::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure338::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure338::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_jetty_cfg_with_jetty_grp，Invalid token with unshared jfr.。";
}

std::string UrmaFailure338::GetId() const
{
    return "urma_338";
}
} // namespace diag
