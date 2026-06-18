#include "urma_failure_369.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure369> g_urma("urma_369");

bool UrmaFailure369::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_jfc") != std::string::npos &&
           message.find("Failed to delete pjfc") != std::string::npos;
}

std::string UrmaFailure369::GetName() const
{
    return "下层资源删除失败导致删除JFC失败";
}

std::string UrmaFailure369::GetRootCauseDesc() const
{
    return "bondp_delete_jfc清理JFC时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure369::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure369::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure369::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jfc，Failed to delete pjfc。";
}

std::string UrmaFailure369::GetId() const
{
    return "urma_369";
}
} // namespace diag
