#include "urma_failure_543.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure543> g_urma("urma_543");

bool UrmaFailure543::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'read_eid_sysfs_with_index' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to read sysfs file')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure543::GetName() const
{
    return "read_eid_sysfs_with_index URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断";
}

std::string UrmaFailure543::GetRootCauseDesc() const
{
    return "read_eid_sysfs_with_index 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl "
           "返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 设备 状态。";
}

RootCause UrmaFailure543::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure543::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure543::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to read sysfs file";
}

std::string UrmaFailure543::GetId() const
{
    return "urma_543";
}

} // namespace diag
