#include "urma_failure_067.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure067> g_urma("urma_067");

bool UrmaFailure067::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_set_jetty_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jetty->jetty_cfg.shared.jfc is not exist'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure067::GetName() const
{
    return "urma_cmd_set_jetty_opt 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure067::GetRootCauseDesc() const
{
    return "urma_cmd_set_jetty_opt 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure067::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure067::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure067::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jetty->jetty_cfg.shared.jfc is not exist";
}

std::string UrmaFailure067::GetId() const
{
    return "urma_067";
}

} // namespace diag
