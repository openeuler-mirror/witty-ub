#include "urma_failure_175.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure175> g_urma("urma_175");

bool UrmaFailure175::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_set_tp_attr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed in ioctl set_tp_attr, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure175::GetName() const
{
    return "设置ioctl的ioctl调用返回失败";
}

std::string UrmaFailure175::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交设置ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。";
}

RootCause UrmaFailure175::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure175::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure175::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_tp_attr，Failed in ioctl set_tp_attr, ret:。";
}

std::string UrmaFailure175::GetId() const
{
    return "urma_175";
}

} // namespace diag
