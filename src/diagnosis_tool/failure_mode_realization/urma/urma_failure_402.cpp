#include "urma_failure_402.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure402> g_urma("urma_402");

bool UrmaFailure402::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Failed to create jfce, dev_name:' | grep -F ', eid_idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure402::GetName() const
{
    return "JFCE创建时下层资源准备失败";
}

std::string UrmaFailure402::GetRootCauseDesc() const
{
    return "函数负责创建JFCE，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure402::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure402::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure402::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_deactive_jfr，[DRV_ERR]Failed to create jfce, dev_name:，, eid_idx:";
}

std::string UrmaFailure402::GetId() const
{
    return "urma_402";
}

} // namespace diag
