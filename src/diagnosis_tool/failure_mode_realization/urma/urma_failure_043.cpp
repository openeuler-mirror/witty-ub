#include "urma_failure_043.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure043> g_urma("urma_043");

bool UrmaFailure043::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_open_provider' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'open failed, err:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure043::GetName() const
{
    return "设备、EID、端口、能力或字符设备路径信息的sysfs读取或解析失败";
}

std::string UrmaFailure043::GetRootCauseDesc() const
{
    return "函数需要从sysfs获取设备、EID、端口、能力或字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导"
           "致URMA无法完成设备发现或能力初始化。";
}

RootCause UrmaFailure043::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure043::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure043::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_open_provider，open failed, err:。";
}

std::string UrmaFailure043::GetId() const
{
    return "urma_043";
}

} // namespace diag
