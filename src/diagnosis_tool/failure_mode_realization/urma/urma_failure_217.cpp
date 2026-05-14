#include "urma_failure_217.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure217> g_urma("urma_217");

bool UrmaFailure217::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_segment_uninit_comp_attr' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to unregister segment, token_id:, handle')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure217::GetName() const
{
    return "bondp_segment_uninit_comp_attr 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure217::GetRootCauseDesc() const
{
    return "bondp_segment_uninit_comp_attr 在初始化或注册设备时未能打开 provider "
           "动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider "
           "操作集。";
}

RootCause UrmaFailure217::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure217::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure217::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to unregister segment, token_id:, handle";
}

std::string UrmaFailure217::GetId() const
{
    return "urma_217";
}

} // namespace diag
