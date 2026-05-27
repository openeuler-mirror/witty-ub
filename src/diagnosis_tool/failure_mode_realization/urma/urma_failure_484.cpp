#include "urma_failure_484.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure484> g_urma("urma_484");

bool UrmaFailure484::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_device_attr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to get cdev_path, dev_name:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure484::GetName() const
{
    return "EID信息的sysfs读取或解析失败";
}

std::string UrmaFailure484::GetRootCauseDesc() const
{
    return "函数需要从sysfs获取EID信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或能力初始"
           "化。";
}

RootCause UrmaFailure484::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure484::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure484::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_device_attr，Failed to get cdev_path, dev_name:。";
}

std::string UrmaFailure484::GetId() const
{
    return "urma_484";
}

} // namespace diag
