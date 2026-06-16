#include "urma_failure_386.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure386> g_urma("urma_386");

bool UrmaFailure386::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfc_batch' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to alloc memory.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure386::GetName() const
{
    return "JFC相关临时结构或命令参数分配失败";
}

std::string UrmaFailure386::GetRootCauseDesc() const
{
    return "函数在分配JFC前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure386::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure386::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure386::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfc_batch，Failed to alloc memory.。";
}

std::string UrmaFailure386::GetId() const
{
    return "urma_386";
}

} // namespace diag
