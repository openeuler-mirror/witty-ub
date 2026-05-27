#include "urma_failure_326.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure326> g_urma("urma_326");

bool UrmaFailure326::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_pjfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create vjfc, dev_name:' | grep -F ', eid_idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure326::GetName() const
{
    return "虚拟 JFC创建时下层资源准备失败";
}

std::string UrmaFailure326::GetRootCauseDesc() const
{
    return "函数负责创建虚拟 JFC，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure326::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure326::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure326::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_pjfc，Failed to create vjfc, dev_name:，, eid_idx:";
}

std::string UrmaFailure326::GetId() const
{
    return "urma_326";
}

} // namespace diag
