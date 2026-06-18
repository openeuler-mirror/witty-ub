#include "urma_failure_581.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure581> g_urma("urma_581");

bool UrmaFailure581::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfr_batch") != std::string::npos &&
           message.find("Failed to delete jfr batch.") != std::string::npos;
}

std::string UrmaFailure581::GetName() const
{
    return "下层资源删除失败导致删除JFR失败";
}

std::string UrmaFailure581::GetRootCauseDesc() const
{
    return "urma_delete_jfr_batch清理JFR时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure581::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure581::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure581::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfr_batch，Failed to delete jfr batch.。";
}

std::string UrmaFailure581::GetId() const
{
    return "urma_581";
}
} // namespace diag
