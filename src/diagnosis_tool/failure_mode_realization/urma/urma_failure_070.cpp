#include "urma_failure_070.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure070> g_urma("urma_070");

bool UrmaFailure070::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jetty_p_vjetty_info' \"$URMA_LOG_PATH\" 2>/dev/null | grep "
        "-F 'UB device must use shared jfr when create jetty.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure070::GetName() const
{
    return "设备创建时下层资源准备失败";
}

std::string UrmaFailure070::GetRootCauseDesc() const
{
    return "函数负责创建设备，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure070::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure070::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure070::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_del_jetty_p_vjetty_info，UB device must use shared jfr when "
           "create jetty.。";
}

std::string UrmaFailure070::GetId() const
{
    return "urma_070";
}

} // namespace diag
