#include "urma_failure_230.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure230> g_urma("urma_230");

bool UrmaFailure230::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'set_write_wr_ptseg_ptjetty' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'bondp_find_vtseg_by_va fail')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure230::GetName() const
{
    return "set_write_wr_ptseg_ptjetty 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure230::GetRootCauseDesc() const
{
    return "set_write_wr_ptseg_ptjetty 在初始化或注册设备时未能打开 provider "
           "动态库、获取动态库路径、匹配驱动名称或完成 provider 注册，导致 URMA 用户态无法绑定对应设备的 provider "
           "操作集。";
}

RootCause UrmaFailure230::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure230::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure230::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：bondp_find_vtseg_by_va fail";
}

std::string UrmaFailure230::GetId() const
{
    return "urma_230";
}

} // namespace diag
