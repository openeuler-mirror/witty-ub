#include "urma_failure_526.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure526> g_urma("urma_526");

bool UrmaFailure526::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_pseg' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to import pseg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure526::GetName() const
{
    return "Segment导入时下层资源准备失败";
}

std::string UrmaFailure526::GetRootCauseDesc() const
{
    return "函数负责导入Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure526::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure526::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure526::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_unimport_pseg，Failed to import pseg。";
}

std::string UrmaFailure526::GetId() const
{
    return "urma_526";
}

} // namespace diag
