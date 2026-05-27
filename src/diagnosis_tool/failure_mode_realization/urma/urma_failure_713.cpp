#include "urma_failure_713.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure713> g_urma("urma_713");

bool UrmaFailure713::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_discover_devices' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'open failed, errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure713::GetName() const
{
    return "设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败";
}

std::string UrmaFailure713::GetRootCauseDesc() const
{
    return "函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导"
           "致URMA无法完成设备发现或能力初始化。";
}

RootCause UrmaFailure713::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure713::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure713::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_discover_devices，open failed, errno:。";
}

std::string UrmaFailure713::GetId() const
{
    return "urma_713";
}

} // namespace diag
