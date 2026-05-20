#include "urma_failure_537.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure537> g_urma("urma_537");

bool UrmaFailure537::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_read_sysfs_file' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'snprintf failed'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure537::GetName() const
{
    return "urma_read_sysfs_file 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用";
}

std::string UrmaFailure537::GetRootCauseDesc() const
{
    return "urma_read_sysfs_file 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA "
           "设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID "
           "信息无法被用户态正确使用。";
}

RootCause UrmaFailure537::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure537::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure537::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：snprintf failed";
}

std::string UrmaFailure537::GetId() const
{
    return "urma_537";
}

} // namespace diag
