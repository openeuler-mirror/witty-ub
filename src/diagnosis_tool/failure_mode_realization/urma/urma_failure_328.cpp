#include "urma_failure_328.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure328> g_urma("urma_328");

bool UrmaFailure328::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_cmd_delete_jfc_batch' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'jfc not from the same dev, cannot delete in a batch, index:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure328::GetName() const
{
    return "urma_cmd_delete_jfc_batch 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure328::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfc_batch 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure328::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure328::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure328::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jfc not from the same dev, cannot delete in a batch, index";
}

std::string UrmaFailure328::GetId() const
{
    return "urma_328";
}

} // namespace diag
