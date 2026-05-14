#include "urma_failure_068.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure068> g_urma("urma_068");

bool UrmaFailure068::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_cmd_set_jetty_opt' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'jetty->jetty_cfg.shared.jfr is not exist')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure068::GetName() const
{
    return "urma_cmd_set_jetty_opt 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure068::GetRootCauseDesc() const
{
    return "urma_cmd_set_jetty_opt 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure068::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure068::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure068::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jetty->jetty_cfg.shared.jfr is not exist";
}

std::string UrmaFailure068::GetId() const
{
    return "urma_068";
}

} // namespace diag
