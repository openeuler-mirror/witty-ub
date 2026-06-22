#include "urma_failure_015.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure015> g_urma("urma_015");

bool UrmaFailure015::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_jfr") != std::string::npos &&
           message.find("Failed to init active indices") != std::string::npos;
}

std::string UrmaFailure015::GetName() const
{
    return "导入JFR执行失败导致导入JFR失败";
}

std::string UrmaFailure015::GetRootCauseDesc() const
{
    return "bondp_import_jfr导入JFR时初始化端口索引或目标端端口索引失败，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure015::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure015::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure015::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_jfr，Failed to init active indices。";
}

std::string UrmaFailure015::GetId() const
{
    return "urma_015";
}
} // namespace diag
