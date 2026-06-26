#include "urma_failure_302.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure302> g_urma("urma_302");

bool UrmaFailure302::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("import_check_tseg_by_import_result") != std::string::npos &&
           message.find("No valid imported route for health check seg") != std::string::npos;
}

std::string UrmaFailure302::GetName() const
{
    return "TSEG、result状态不满足要求导致导入TSEG、result失败";
}

std::string UrmaFailure302::GetRootCauseDesc() const
{
    return "import_check_tseg_by_import_"
           "result执行导入TSEG、result时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure302::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure302::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure302::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：import_check_tseg_by_import_result，No valid imported route for health "
           "check s"
           "eg。";
}

std::string UrmaFailure302::GetId() const
{
    return "urma_302";
}
} // namespace diag
