#include "urma_failure_521.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure521> g_urma("urma_521");

bool UrmaFailure521::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_pseg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to import pseg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure521::GetName() const
{
    return "Segment导入时下层资源准备失败";
}

std::string UrmaFailure521::GetRootCauseDesc() const
{
    return "函数负责导入Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure521::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure521::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure521::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_unimport_pseg，Failed to import pseg";
}

std::string UrmaFailure521::GetId() const
{
    return "urma_521";
}

} // namespace diag
