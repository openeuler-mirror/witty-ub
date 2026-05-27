#include "urma_failure_479.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure479> g_urma("urma_479");

bool UrmaFailure479::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_ioctl_get_eid_list' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to open urma cdev with path'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure479::GetName() const
{
    return "EID信息的sysfs读取或解析失败";
}

std::string UrmaFailure479::GetRootCauseDesc() const
{
    return "函数需要从sysfs获取EID信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始"
           "化。";
}

RootCause UrmaFailure479::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure479::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure479::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_ioctl_get_eid_list，Failed to open urma cdev with path";
}

std::string UrmaFailure479::GetId() const
{
    return "urma_479";
}

} // namespace diag
