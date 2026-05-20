#include "urma_failure_548.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure548> g_urma("urma_548");

bool UrmaFailure548::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_parse_rsvd_jetty_range' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'parse sysfs: failed'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure548::GetName() const
{
    return "urma_parse_rsvd_jetty_range 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用";
}

std::string UrmaFailure548::GetRootCauseDesc() const
{
    return "urma_parse_rsvd_jetty_range 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA "
           "设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID "
           "信息无法被用户态正确使用。";
}

RootCause UrmaFailure548::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure548::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure548::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：parse sysfs: failed";
}

std::string UrmaFailure548::GetId() const
{
    return "urma_548";
}

} // namespace diag
