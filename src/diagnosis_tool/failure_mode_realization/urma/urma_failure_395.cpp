#include "urma_failure_395.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure395> g_urma("urma_395");

bool UrmaFailure395::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Failed to create jfr, dev_name:' | grep -F ', eid_idex:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure395::GetName() const
{
    return "JFR创建时下层资源准备失败";
}

std::string UrmaFailure395::GetRootCauseDesc() const
{
    return "函数负责创建JFR，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure395::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure395::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure395::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_deactive_jfs，[DRV_ERR]Failed to create jfr, dev_name:，, eid_idex:";
}

std::string UrmaFailure395::GetId() const
{
    return "urma_395";
}

} // namespace diag
