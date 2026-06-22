#include "urma_failure_368.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure368> g_urma("urma_368");

bool UrmaFailure368::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_jfc") != std::string::npos &&
           message.find("Failed to delete vjfc") != std::string::npos;
}

std::string UrmaFailure368::GetName() const
{
    return "下层资源删除失败导致删除JFC失败";
}

std::string UrmaFailure368::GetRootCauseDesc() const
{
    return "bondp_delete_jfc清理JFC时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure368::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure368::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure368::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jfc，Failed to delete vjfc。";
}

std::string UrmaFailure368::GetId() const
{
    return "urma_368";
}
} // namespace diag
