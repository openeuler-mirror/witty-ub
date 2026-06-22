#include "urma_failure_116.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure116> g_urma("urma_116");

bool UrmaFailure116::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_import_jetty_async") != std::string::npos &&
           message.find("Failed to alloc incomplete_tjetty.") != std::string::npos;
}

std::string UrmaFailure116::GetName() const
{
    return "urma notifier incompletejetty分配失败导致导入Jetty失败";
}

std::string UrmaFailure116::GetRootCauseDesc() const
{
    return "urma_import_jetty_async执行导入Jetty前需要准备urma notifier "
           "incompletejetty，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure116::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure116::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure116::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_import_jetty_async，Failed to alloc incomplete_tjetty.。";
}

std::string UrmaFailure116::GetId() const
{
    return "urma_116";
}
} // namespace diag
