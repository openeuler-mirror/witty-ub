#include "urma_failure_042.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure042> g_urma("urma_042");

bool UrmaFailure042::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_open_provider") != std::string::npos &&
           message.find("realpath failed.") != std::string::npos;
}

std::string UrmaFailure042::GetName() const
{
    return "打开provider执行失败导致打开provider失败";
}

std::string UrmaFailure042::GetRootCauseDesc() const
{
    return "urma_open_provider执行打开provider时依赖的打开provider步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure042::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure042::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure042::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_open_provider，realpath failed.。";
}

std::string UrmaFailure042::GetId() const
{
    return "urma_042";
}
} // namespace diag
