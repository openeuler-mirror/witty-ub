#include "urma_failure_497.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure497> g_urma("urma_497");

bool UrmaFailure497::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'get_bjetty_ctx_by_cr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Null bjetty_ctx in bdp_comp'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure497::GetName() const
{
    return "get_bjetty_ctx_by_cr 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure497::GetRootCauseDesc() const
{
    return "get_bjetty_ctx_by_cr 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure497::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure497::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure497::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Null bjetty_ctx in bdp_comp";
}

std::string UrmaFailure497::GetId() const
{
    return "urma_497";
}

} // namespace diag
