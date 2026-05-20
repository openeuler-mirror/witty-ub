#include "urma_failure_313.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure313> g_urma("urma_313");

bool UrmaFailure313::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_delete_jfs_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfs not from the same dev, cannot delete in a batch, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure313::GetName() const
{
    return "urma_cmd_delete_jfs_batch 装载或匹配 provider 失败导致设备驱动能力不可用";
}

std::string UrmaFailure313::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfs_batch 在初始化或注册设备时未能打开 provider 动态库、获取动态库路径、匹配驱动名称或完成 "
           "provider 注册，导致 URMA 用户态无法绑定对应设备的 provider 操作集。";
}

RootCause UrmaFailure313::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure313::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure313::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jfs not from the same dev, cannot delete in a batch, index";
}

std::string UrmaFailure313::GetId() const
{
    return "urma_313";
}

} // namespace diag
