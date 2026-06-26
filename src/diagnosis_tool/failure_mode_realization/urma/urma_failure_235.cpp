#include "urma_failure_235.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure235> g_urma("urma_235");

bool UrmaFailure235::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_seg") != std::string::npos &&
           message.find("Failed to alloc target seg") != std::string::npos;
}

std::string UrmaFailure235::GetName() const
{
    return "bondp importseg分配失败导致导入Segment失败";
}

std::string UrmaFailure235::GetRootCauseDesc() const
{
    return "bondp_import_seg执行导入Segment前需要准备bondp importseg，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure235::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure235::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure235::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_seg，Failed to alloc target seg。";
}

std::string UrmaFailure235::GetId() const
{
    return "urma_235";
}
} // namespace diag
