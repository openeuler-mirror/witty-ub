#include "urma_failure_570.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure570> g_urma("urma_570");

bool UrmaFailure570::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_v_segment_register' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Fail to register seg, ret')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure570::GetName() const
{
    return "bondp_v_segment_register 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure570::GetRootCauseDesc() const
{
    return "bondp_v_segment_register 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure570::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure570::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure570::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Fail to register seg, ret";
}

std::string UrmaFailure570::GetId() const
{
    return "urma_570";
}

} // namespace diag
