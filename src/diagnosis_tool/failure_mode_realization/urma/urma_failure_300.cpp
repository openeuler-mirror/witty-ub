#include "urma_failure_300.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure300> g_urma("urma_300");

bool UrmaFailure300::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jetty_grp' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Failed to import seg, dev_name:' | grep -F ', eid_idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure300::GetName() const
{
    return "Segment导入时下层资源准备失败";
}

std::string UrmaFailure300::GetRootCauseDesc() const
{
    return "函数负责导入Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure300::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure300::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure300::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jetty_grp，[DRV_ERR]Failed to import seg, dev_name:，, eid_idx:";
}

std::string UrmaFailure300::GetId() const
{
    return "urma_300";
}

} // namespace diag
