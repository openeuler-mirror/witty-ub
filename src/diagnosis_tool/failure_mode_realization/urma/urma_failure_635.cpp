#include "urma_failure_635.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure635> g_urma("urma_635");

bool UrmaFailure635::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'post_send_check_jfs_wr_valid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'when set write_wr, either of src/dst num_sge/sge has been set zero or NULL'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure635::GetName() const
{
    return "post_send_check_jfs_wr_valid 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用";
}

std::string UrmaFailure635::GetRootCauseDesc() const
{
    return "post_send_check_jfs_wr_valid 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA "
           "设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID "
           "信息无法被用户态正确使用。";
}

RootCause UrmaFailure635::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure635::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure635::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：when set write_wr, either of src/dst num_sge/sge has been set zero or "
           "NULL";
}

std::string UrmaFailure635::GetId() const
{
    return "urma_635";
}

} // namespace diag
