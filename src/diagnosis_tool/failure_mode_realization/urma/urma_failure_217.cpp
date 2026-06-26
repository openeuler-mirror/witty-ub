#include "urma_failure_217.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure217> g_urma("urma_217");

bool UrmaFailure217::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_context") != std::string::npos &&
           message.find("[DRV_ERR]Failed to create urma context.") != std::string::npos;
}

std::string UrmaFailure217::GetName() const
{
    return "下层资源创建失败导致创建context失败";
}

std::string UrmaFailure217::GetRootCauseDesc() const
{
    return "urma_create_context在创建context过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure217::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure217::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure217::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_context，[DRV_ERR]Failed to create urma context.。";
}

std::string UrmaFailure217::GetId() const
{
    return "urma_217";
}
} // namespace diag
